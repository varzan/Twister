/*
File: Main.java ; This file is part of Twister.
Version: 3.002

Copyright (C) 2012-2013 , Luxoft

Authors: Andrei Costachi <acostachi@luxoft.com>
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
import java.awt.Image;
import java.awt.event.ComponentAdapter;
import java.awt.event.ComponentEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.net.URL;
import javax.imageio.ImageIO;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;

import com.twister.CustomDialog;

/*
 * main method for starting Twister local
 */
public class Main{
    
    public static void main(String args[]){
        try {
            URL url = new URL("http://tsc-server/twister_gui/logo.png");
            RunnerRepository.logo = ImageIO.read(url).getScaledInstance(230, 100, Image.SCALE_FAST);
        } catch (Exception e) {
            e.printStackTrace();
        }
        readLogoTxt();
        PermissionValidator.init("CREATE_PROJECT,CHANGE_PROJECT,DELETE_PROJECT,CHANGE_PLUGINS,"+
                                 "CHANGE_FWM_CFG,CHANGE_GLOBALS,RUN_TESTS,EDIT_TC,"+
                                 "CHANGE_DB_CFG,CHANGE_EML_CFG,CHANGE_SERVICES,CHANGE_SUT,CHANGE_TESTBED,LOCK_SUT,LOCK_TESTBED,RESTART_SERVER");
        final JFrame f = new JFrame();
        f.setVisible(true);
        f.setBounds(0,0,800,600);
        f.addComponentListener(new ComponentAdapter(){
            public void componentResized(ComponentEvent e){
                if(RunnerRepository.window!=null){
                    RunnerRepository.setSize(f.getWidth(), f.getHeight());
                }}});
        f.addWindowListener(new WindowAdapter(){
                public void windowClosing(WindowEvent e){
                    RunnerRepository.saveMainLayout();
                    RunnerRepository.window.mainpanel.p4.getPlugins().uploadPluginsFile();
                    int r = (Integer)CustomDialog.showDialog(
                                new JLabel("Save your Project XML before exiting ?"),
                                JOptionPane.QUESTION_MESSAGE, 
                                JOptionPane.OK_CANCEL_OPTION, RunnerRepository.window.mainpanel, "Save", null);
                    if(r == JOptionPane.OK_OPTION){RunnerRepository.window.mainpanel.saveUserXML();}
                    if(RunnerRepository.window.deleteTemp(new File(RunnerRepository.temp)))
                        System.out.println(RunnerRepository.temp+
                                            System.getProperty("file.separator")+
                                            "Twister deleted successfull");
                    else System.out.println("Could not delete: "+RunnerRepository.temp+
                                            RunnerRepository.getBar()+"Twister");
                    f.dispose();
                    RunnerRepository.run = false;
                    RunnerRepository.window.mainpanel.p4.getTB().releaseAllResources();
                    RunnerRepository.window.mainpanel.p4.getSut().sut.getSutTree().releaseAllSuts();
                    System.exit(0);}});
        f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
//         RunnerRepository.host = "10.3.1.203";
//         RunnerRepository.user = "twister";
//         RunnerRepository.password = "twister";
        RunnerRepository.host = "tsc-server";
//         RunnerRepository.user = "tscguest";
//         RunnerRepository.password = "tscguest";
//         RunnerRepository.host = "11.126.32.14";
//         RunnerRepository.host = "11.126.32.21";
//         RunnerRepository.user = "user";
//         RunnerRepository.password = "password";
        RunnerRepository.user = "bogdan";
        RunnerRepository.password = "atmneuro";
//         RunnerRepository.user = "guest";
//         RunnerRepository.password = "guest";
        RunnerRepository.CENTRALENGINEPORT = "8000";
//         RunnerRepository.host = "11.126.32.20";
//         RunnerRepository.user = "nisuser";
//         RunnerRepository.password = "nispass";
        RunnerRepository.initialize("false",RunnerRepository.host,f.getContentPane(),null);
        //TestGui tg = new TestGui();
    }

    public static void readLogoTxt(){
        try{
            URL logo = new URL("http://tsc-server/twister_gui/logo.txt");
            BufferedReader in = new BufferedReader(
            new InputStreamReader(logo.openStream()));
            
            StringBuilder sb = new StringBuilder();
            String inputLine;
            while ((inputLine = in.readLine()) != null){
                sb.append(inputLine);
                sb.append("\n");
            }
            in.close();
            RunnerRepository.logotxt = sb.toString();
        } catch(Exception e){
            e.printStackTrace();
        }
    }

}
